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
    document.getElementById('kpi-max-country').textContent = DATA.summary.max_country;
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

  // 색상 척도
  const colorScale = d3.scaleSequential()
    .domain([0, 100])
    .interpolator(d3.interpolateRgbBasis(['#1a9641','#a6d96a','#ffffbf','#fd8d3c','#d73027']));

  // iso3 → 데이터 맵
  const countryMap = {};
  DATA.countries.forEach(c => { if (c.iso3) countryMap[c.iso3] = c; });

  // 투영
  const projection = d3.geoNaturalEarth1()
    .scale(W / 6.3).translate([W / 2, H / 2]);
  const path = d3.geoPath().projection(projection);

  // 배경 그라디언트
  const defs = svg.append('defs');
  defs.append('radialGradient').attr('id','map-bg-grad')
    .selectAll('stop').data([
      {offset:'0%', color:'rgba(13,18,48,1)'},
      {offset:'100%', color:'rgba(8,12,30,1)'}
    ]).join('stop').attr('offset', d=>d.offset).attr('stop-color', d=>d.color);

  svg.append('rect').attr('width', W).attr('height', H)
    .attr('fill', 'url(#map-bg-grad)');

  const tooltip = document.getElementById('map-tooltip');
  const panel   = document.getElementById('country-panel');

  // World TopoJSON
  try {
    const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
    const countries = topojson.feature(world, world.objects.countries);

    // iso3 변환 함수 (numeric → alpha3)
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
        return c && c.lp != null ? colorScale(c.lp) : '#1e2540';
      })
      .attr('stroke', '#0d1230').attr('stroke-width', 0.5)
      .attr('class', 'country-path')
      .on('mouseover', function(event, d) {
        const iso3 = numMap[String(d.id).padStart(3,'0')];
        const c = iso3 && countryMap[iso3];
        if (!c) return;
        d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
        tooltip.innerHTML = `<strong>${c.name}</strong><br>Learning Poverty: <strong>${c.lp != null ? c.lp.toFixed(1)+'%' : 'N/A'}</strong>`;
        tooltip.classList.remove('hidden');
        positionTooltip(event, tooltip);
      })
      .on('mousemove', function(event) {
        positionTooltip(event, tooltip);
      })
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
    console.warn('TopoJSON 로드 실패, 대체 표시');
    svg.append('text').attr('x', W/2).attr('y', H/2)
      .attr('text-anchor','middle').attr('fill','#6b7a99')
      .text('지도 로드 실패 — 네트워크 연결을 확인하세요.');
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
  const lp = c.lp != null ? c.lp.toFixed(1) : 'N/A';
  badge.textContent = lp + (c.lp != null ? '%' : '');
  const color = c.lp > 70 ? '#e74c3c' : c.lp > 40 ? '#f39c12' : '#27ae60';
  badge.style.background = color + '22';
  badge.style.color = color;

  const stats = [
    ['1인당 GDP', c.gdp != null ? '$' + Math.round(c.gdp).toLocaleString() : 'N/A'],
    ['거버넌스 지수', c.governance != null ? c.governance.toFixed(2) : 'N/A'],
    ['의사 수 /1000명', c.physicians != null ? c.physicians.toFixed(2) : 'N/A'],
    ['10대 출산율', c.teen_birth != null ? c.teen_birth.toFixed(1) : 'N/A'],
    ['교사-학생 비율', c.pupil_teacher != null ? '1:' + Math.round(c.pupil_teacher) : 'N/A'],
    ['전기 보급률', c.electricity != null ? c.electricity.toFixed(1) + '%' : 'N/A'],
  ];
  document.getElementById('panel-stats').innerHTML = stats.map(([k, v]) =>
    `<div class="panel-stat-row"><span class="panel-stat-label">${k}</span><span class="panel-stat-val">${v}</span></div>`
  ).join('');

  const devMap = { positive:'긍정적 이탈자 — GDP 대비 현저히 낮은 LP 달성', negative:'부정적 이탈자 — GDP 대비 높은 LP 기록', middle:'중간 집단' };
  const devClass = { positive:'dev-positive', negative:'dev-negative', middle:'dev-middle' };
  document.getElementById('panel-deviance').innerHTML =
    `<div class="panel-deviance ${devClass[c.deviance_group] || 'dev-middle'}">${devMap[c.deviance_group] || '—'}</div>`;

  panel.classList.remove('hidden');
}

// ── v1.0 vs v2.0 요인 비교 차트 ─────────────────────────
function buildFactorsCharts() {
  // v1.0: 상관계수 기반 (보고서 기준)
  const v1Labels = ['10대 출산율','유아 사망률','전기 보급률','의사 수','초등 수료율'];
  const v1Values = [0.837, 0.879, 0.795, 0.733, 0.648]; // |r| 절대값

  new Chart(document.getElementById('factorsV1Chart'), {
    type: 'bar',
    data: {
      labels: v1Labels,
      datasets: [{ label: '|상관계수|', data: v1Values,
        backgroundColor: 'rgba(127,140,141,0.5)', borderColor: '#7f8c8d',
        borderWidth: 1, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { min: 0, max: 1, ticks: { color: '#a8b5d0', font:{size:11} }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });

  // v2.0: 변수 잔차화 Cohen's d (유의 5개)
  const sig = DATA.a1_factors.filter(f => f.p_value < 0.05).slice(0, 5);
  const v2Labels = sig.map(f => f.label);
  const v2Values = sig.map(f => Math.abs(f.cohens_d));
  const v2Colors = sig.map(f => f.cohens_d > 0 ? 'rgba(79,142,247,0.6)' : 'rgba(231,76,60,0.6)');
  const v2Borders = sig.map(f => f.cohens_d > 0 ? '#4f8ef7' : '#e74c3c');

  new Chart(document.getElementById('factorsV2Chart'), {
    type: 'bar',
    data: {
      labels: v2Labels,
      datasets: [{ label: "|Cohen's d|", data: v2Values,
        backgroundColor: v2Colors, borderColor: v2Borders,
        borderWidth: 1, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { min: 0, max: 1.2, ticks: { color: '#a8b5d0', font:{size:11} }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });
}

// ── A1 산점도 (D3.js) ────────────────────────────────────
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

  // 회귀선
  const xMean = d3.mean(valid, d=>d.log_gdp);
  const yMean = d3.mean(valid, d=>d.lp);
  const num = d3.sum(valid, d=>(d.log_gdp - xMean)*(d.lp - yMean));
  const den = d3.sum(valid, d=>(d.log_gdp - xMean)**2);
  const slope = num/den, intercept = yMean - slope*xMean;
  const xExt = d3.extent(valid, d=>d.log_gdp);
  svg.append('line')
    .attr('x1', xScale(xExt[0])).attr('y1', yScale(intercept + slope*xExt[0]))
    .attr('x2', xScale(xExt[1])).attr('y2', yScale(intercept + slope*xExt[1]))
    .attr('stroke', '#4f8ef7').attr('stroke-width', 1.5).attr('stroke-dasharray','6,4').attr('opacity',0.6);

  // 색상
  const colorOf = g => g==='positive' ? '#27ae60' : g==='negative' ? '#e74c3c' : '#4a5568';

  // 점
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
      tt.innerHTML = `<strong>${d.name}</strong><br>LP: ${d.lp?.toFixed(1)}% | GDP: $${Math.round(d.gdp||0).toLocaleString()}<br>잔차: ${d.residual?.toFixed(1)}%p`;
      tt.classList.remove('hidden');
      positionTooltip(event, tt);
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', d.deviance_group!=='middle' ? 6 : 4);
      document.getElementById('map-tooltip').classList.add('hidden');
    });

  // TOP 5 국가명 레이블
  const top5Names = (DATA.top_deviants||[]).map(d=>d.country);
  valid.filter(c=>top5Names.includes(c.name)).forEach(c => {
    svg.append('text')
      .attr('x', xScale(c.log_gdp)+8).attr('y', yScale(c.lp)+4)
      .attr('fill','#27ae60').attr('font-size',10).attr('font-weight','700')
      .text(c.name);
  });

  // 축
  svg.append('g').attr('transform', `translate(0,${iH})`)
    .call(d3.axisBottom(xScale).ticks(6).tickFormat(d=>`log(GDP)=${d.toFixed(1)}`))
    .selectAll('text').style('fill','#a8b5d0').style('font-size','10px');
  svg.append('g').call(d3.axisLeft(yScale).ticks(6).tickFormat(d=>d+'%'))
    .selectAll('text').style('fill','#a8b5d0').style('font-size','10px');
  svg.selectAll('.domain, .tick line').attr('stroke','rgba(255,255,255,0.1)');

  svg.append('text').attr('x', iW/2).attr('y', iH+42)
    .attr('text-anchor','middle').attr('fill','#6b7a99').attr('font-size',11)
    .text('log(1인당 GDP)');
  svg.append('text').attr('transform','rotate(-90)').attr('x', -iH/2).attr('y', -38)
    .attr('text-anchor','middle').attr('fill','#6b7a99').attr('font-size',11)
    .text('Learning Poverty (%)');
}

// ── TOP 5 카드 ───────────────────────────────────────────
function buildTop5() {
  const container = document.getElementById('top5-cards');
  if (!DATA.top_deviants) return;
  container.innerHTML = DATA.top_deviants.map(d => `
    <div class="top5-card">
      <div class="top5-rank">#${d.rank}</div>
      <div class="top5-info">
        <div class="top5-country">${d.country}</div>
        <div class="top5-detail">실제 ${d.lp.toFixed(1)}% · 예측 ${d.predicted.toFixed(1)}%</div>
      </div>
      <div class="top5-residual">${d.residual.toFixed(1)}%p</div>
    </div>
  `).join('');
}

// ── Cohen's d 막대 차트 ──────────────────────────────────
function buildCohensD() {
  const factors = [...DATA.a1_factors].sort((a,b)=>a.cohens_d - b.cohens_d);
  const labels = factors.map(f=>f.label);
  const vals   = factors.map(f=>f.cohens_d);
  const colors = factors.map(f =>
    f.significant ? (f.cohens_d > 0 ? 'rgba(79,142,247,0.7)' : 'rgba(231,76,60,0.7)')
    : f.tendency   ? 'rgba(243,156,18,0.6)'
    : 'rgba(127,140,141,0.4)'
  );
  const borders = factors.map(f =>
    f.significant ? (f.cohens_d > 0 ? '#4f8ef7' : '#e74c3c')
    : f.tendency   ? '#f39c12' : '#7f8c8d'
  );

  new Chart(document.getElementById('cohensDChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: "Cohen's d", data: vals,
        backgroundColor: colors, borderColor: borders,
        borderWidth: 1, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const f = factors[ctx.dataIndex];
              return [`d=${f.cohens_d.toFixed(2)}`, `p=${f.p_value.toFixed(4)}`, f.significant ? '✅ 유의' : f.tendency ? '⚠️ 경향' : '❌ 비유의'];
            }
          }
        }
      },
      scales: {
        x: {
          min: -1.1, max: 1.1,
          ticks: { color: '#a8b5d0', font:{size:11} },
          grid: { color: 'rgba(255,255,255,0.06)' }
        },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });
}

// ── 분위별 히트맵 ─────────────────────────────────────────
function buildQuartileHeatmap() {
  const el = document.getElementById('quartile-heatmap');
  const data = DATA.a1_quartile || [];
  if (!data.length) {
    el.innerHTML = '<p style="color:#6b7a99;font-size:0.82rem;padding:20px;">p&lt;0.10 유의 결과 없음</p>';
    return;
  }

  const quarters = ['Q1','Q2','Q3','Q4'];
  const labels = [...new Set(data.map(d=>d.label))];

  const lookup = {};
  data.forEach(d => { lookup[`${d.label}_${d.quartile}`] = d; });

  const dScale = val => {
    if (val == null) return 'transparent';
    const abs = Math.min(Math.abs(val), 1.4);
    const alpha = 0.15 + (abs/1.4)*0.65;
    return val > 0
      ? `rgba(79,142,247,${alpha.toFixed(2)})`
      : `rgba(231,76,60,${alpha.toFixed(2)})`;
  };

  const thead = `<thead><tr><th>변수</th>${quarters.map(q=>`<th>${q}</th>`).join('')}</tr></thead>`;
  const tbody = '<tbody>' + labels.map(label => {
    const cells = quarters.map(q => {
      const d = lookup[`${label}_${q}`];
      if (!d) return `<td class="heatmap-empty">—</td>`;
      const bg = dScale(d.cohens_d);
      const sig = d.significant ? '✅' : '⚠️';
      return `<td style="background:${bg};padding:8px 6px;" title="d=${d.cohens_d.toFixed(2)}, p=${d.p_value.toFixed(3)}">${sig} ${d.cohens_d.toFixed(2)}</td>`;
    });
    return `<tr><td class="heatmap-label" style="padding:8px 10px;">${label}</td>${cells.join('')}</tr>`;
  }).join('') + '</tbody>';

  el.innerHTML = `<table class="heatmap-table">${thead}${tbody}</table>`;
}

// ── A2 계수 + 부트스트래핑 ────────────────────────────────
function buildA2Charts() {
  const coeffs = DATA.a2.coefficients;
  const labels = coeffs.map(c=>c.label);
  const betas  = coeffs.map(c=>c.beta);
  const colors = coeffs.map(c =>
    c.significant ? (c.beta < 0 ? 'rgba(39,174,96,0.7)' : 'rgba(231,76,60,0.6)')
    : 'rgba(127,140,141,0.4)'
  );

  new Chart(document.getElementById('a2CoeffChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'β (표준화)', data: betas,
        backgroundColor: colors, borderWidth: 1, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const c = coeffs[ctx.dataIndex];
              return [`β=${c.beta.toFixed(3)}`, `p=${c.p_value.toFixed(4)}`, c.significant ? '✅ 유의(p<0.05)' : '❌ 비유의'];
            }
          }
        }
      },
      scales: {
        x: { ticks: { color:'#a8b5d0', font:{size:11} }, grid:{ color:'rgba(255,255,255,0.06)' } },
        y: { ticks: { color:'#a8b5d0', font:{size:11} }, grid:{ display:false } }
      }
    }
  });

  // 부트스트래핑 CI
  const el = document.getElementById('bootstrap-ci-chart');
  const ciData = [
    { label:'교육지출 β₁',    beta:0.08,   ci:[-4.54, 4.70], sig:false },
    { label:'거버넌스 β₂',    beta:-16.60, ci:DATA.a2.boot_gov_ci, sig:true },
    { label:'교호작용 β₃',    beta:0.38,   ci:[-3.13, 4.70], sig:false },
    { label:'GDP 통제 β₄',   beta:-9.80,  ci:[-17.37,-2.22], sig:true },
  ];

  // CI 바 시각화 (상대적 스케일)
  const allVals = ciData.flatMap(d=>[d.ci[0], d.ci[1], d.beta]);
  const minV = Math.min(...allVals), maxV = Math.max(...allVals);
  const range = maxV - minV;
  const toPercent = v => ((v - minV) / range * 100).toFixed(1) + '%';
  const zeroPercent = ((-minV) / range * 100).toFixed(1);

  el.innerHTML = ciData.map(d => {
    const l = toPercent(d.ci[0]), r = toPercent(d.ci[1]);
    const w = ((d.ci[1]-d.ci[0]) / range * 100).toFixed(1);
    const barColor = d.sig ? (d.beta < 0 ? 'rgba(39,174,96,0.5)' : 'rgba(231,76,60,0.5)') : 'rgba(127,140,141,0.3)';
    return `
      <div class="ci-row">
        <div class="ci-label">${d.label}</div>
        <div style="flex:1">
          <div class="ci-track ${d.sig?'ci-sig':'ci-ns'}">
            <div class="ci-bar" style="left:${l};width:${w}%;background:${barColor}"></div>
            <div class="ci-zero" style="left:${zeroPercent}%"></div>
          </div>
          <div class="ci-vals">${d.ci[0].toFixed(1)} ~ ${d.ci[1].toFixed(1)} (β=${d.beta.toFixed(2)})</div>
        </div>
      </div>`;
  }).join('');
}

// ── 정책 제언 카드 ────────────────────────────────────────
function buildPolicyCards() {
  const grid = document.getElementById('policy-grid');
  grid.innerHTML = DATA.policy_recommendations.map(p => `
    <div class="policy-card">
      <div class="policy-number">POLICY 0${p.id}</div>
      <div class="policy-icon">${p.icon}</div>
      <div class="policy-title">${p.title}</div>
      <div class="policy-subtitle">${p.subtitle}</div>
      <div class="policy-headline">${p.headline}</div>
      <div class="policy-evidence">📊 ${p.evidence}</div>
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
