/* app.js — The Silent Crisis v2.0 */

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
  } catch(e) {
    console.error('데이터 로드 실패:', e);
  }
}

// ── NAV 스크롤 ──────────────────────────────────────────
function setupNav() {
  const nav = document.getElementById('nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// ── 카운터 애니메이션 ─────────────────────────────────
function animateCounters() {
  document.querySelectorAll('.counter').forEach(el => {
    const target = parseFloat(el.dataset.target);
    const suffix = el.dataset.suffix || '';
    const duration = 1800;
    const start = performance.now();
    function update(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 4);
      const val = target * ease;
      el.textContent = (target % 1 === 0 ? Math.round(val) : val.toFixed(1)) + suffix;
      if (t < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

// ── 토글 버튼 ──────────────────────────────────────────
function toggleFactorList() {
  const list = document.getElementById('factors-full-list');
  const btn  = document.getElementById('toggle-full-list');
  if (list.classList.contains('open')) {
    list.classList.remove('open');
    btn.textContent = '▼ 17개 요인 전체 순위 보기';
  } else {
    list.classList.add('open');
    btn.textContent = '▲ 닫기';
  }
}
window.toggleFactorList = toggleFactorList;

// ── 세계 지도 (D3.js) ───────────────────────────────────
async function buildMap() {
  const container = document.getElementById('map-container');
  const W = container.clientWidth, H = 520;
  const svg = d3.select('#map-container').append('svg').attr('width', W).attr('height', H);

  // 진한 색상 스케일: 파랑 → 노랑 → 빨강
  const colorScale = d3.scaleSequential()
    .domain([0, 100])
    .interpolator(d3.interpolateRgbBasis(['#0ea5e9', '#facc15', '#ef4444']));

  const countryMap = {};
  DATA.countries.forEach(c => { if (c.iso3) countryMap[c.iso3] = c; });

  const projection = d3.geoNaturalEarth1().scale(W / 6.3).translate([W / 2, H / 2]);
  const path = d3.geoPath().projection(projection);

  svg.append('rect').attr('width', W).attr('height', H).attr('fill', '#080c1e');

  const tooltip = document.getElementById('map-tooltip');

  try {
    const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
    const countries = topojson.feature(world, world.objects.countries);

    const numToAlpha = await fetch(
      'https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.json'
    ).then(r => r.json()).catch(() => []);
    const numMap = {};
    numToAlpha.forEach(d => { numMap[d['country-code']] = d['alpha-3']; });

    svg.append('g')
      .selectAll('path')
      .data(countries.features)
      .join('path')
      .attr('d', path)
      .attr('fill', d => {
        const iso3 = numMap[String(d.id).padStart(3, '0')];
        const c = iso3 && countryMap[iso3];
        return c && c.lp != null ? colorScale(c.lp) : '#2d3748';
      })
      .attr('stroke', '#080c1e').attr('stroke-width', 0.5)
      .attr('class', 'country-path')
      .on('mouseover', function(event, d) {
        const iso3 = numMap[String(d.id).padStart(3, '0')];
        const c = iso3 && countryMap[iso3];
        if (!c) return;
        d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
        tooltip.innerHTML = `<strong>${c.name}</strong><br>Learning Poverty: <strong>${c.lp != null ? c.lp.toFixed(1) + '%' : '데이터 없음'}</strong>`;
        tooltip.classList.remove('hidden');
        positionTooltip(event, tooltip);
      })
      .on('mousemove', function(event) { positionTooltip(event, tooltip); })
      .on('mouseout', function() {
        d3.select(this).attr('stroke', '#080c1e').attr('stroke-width', 0.5);
        tooltip.classList.add('hidden');
      })
      .on('click', function(event, d) {
        const iso3 = numMap[String(d.id).padStart(3, '0')];
        const c = iso3 && countryMap[iso3];
        if (c) showCountryPanel(c);
      });

    svg.append('path')
      .datum(topojson.mesh(world, world.objects.countries, (a, b) => a !== b))
      .attr('d', path).attr('fill', 'none').attr('stroke', '#080c1e').attr('stroke-width', 0.3);
  } catch(e) {
    console.warn('TopoJSON 로드 실패');
  }

  document.getElementById('panel-close').addEventListener('click', () => {
    document.getElementById('country-panel').classList.add('hidden');
  });
}

function positionTooltip(event, el) {
  el.style.left = Math.min(event.clientX + 14, window.innerWidth - 220) + 'px';
  el.style.top  = (event.clientY - 40) + 'px';
  el.style.position = 'fixed';
}

function showCountryPanel(c) {
  const panel = document.getElementById('country-panel');
  document.getElementById('panel-country').textContent = c.name;

  const badge = document.getElementById('panel-lp-badge');
  const lp = c.lp != null ? c.lp.toFixed(1) : '데이터 없음';
  badge.textContent = c.lp != null ? lp + '%' : lp;
  const color = c.lp > 70 ? '#ef4444' : c.lp > 40 ? '#facc15' : '#0ea5e9';
  badge.style.background = color + '22';
  badge.style.color = color;

  const stats = [
    ['GDP (1인당 소득)', c.gdp != null ? '$' + Math.round(c.gdp).toLocaleString() : '정보 없음'],
    ['거버넌스 지수 (시스템 투명성)', c.governance != null ? c.governance.toFixed(2) : '정보 없음'],
    ['의사 수 (1000명당)', c.physicians != null ? c.physicians.toFixed(2) + '명' : '정보 없음'],
    ['10대 소녀 출산율', c.teen_birth != null ? c.teen_birth.toFixed(1) : '정보 없음'],
    ['교사 1인당 학생 수', c.pupil_teacher != null ? Math.round(c.pupil_teacher) + '명' : '정보 없음'],
    ['전기 보급률', c.electricity != null ? c.electricity.toFixed(1) + '%' : '정보 없음'],
  ];
  document.getElementById('panel-stats').innerHTML = stats.map(([k, v]) =>
    `<div class="panel-stat-row"><span class="panel-stat-label">${k}</span><span class="panel-stat-val">${v}</span></div>`
  ).join('');

  panel.classList.remove('hidden');
}

// ── 단순 비교 vs 진짜 중요도 차트 ──────────────────────
function buildFactorsCharts() {
  // 17개 통합 기준 TOP 5 (유아사망률, GDP, 발육부진율, 10대출산율, 여성조혼율)
  const v1Labels = ['유아 사망률', 'GDP (1인당 소득)', '아동 발육부진율', '10대 출산율', '여성 조혼율'];
  const v1Values = [0.878, 0.845, 0.845, 0.837, 0.810];

  new Chart(document.getElementById('factorsV1Chart'), {
    type: 'bar',
    data: {
      labels: v1Labels,
      datasets: [{ label: '상관계수(절댓값)', data: v1Values, backgroundColor: '#475569', borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `상관계수: ${v1Values[ctx.dataIndex].toFixed(3)}`
          }
        }
      },
      scales: {
        x: { min: 0, max: 1, ticks: { color: '#a8b5d0' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font: { size: 11 } }, grid: { display: false } }
      }
    }
  });
}

// ── 산점도 (D3.js) ─────────────────────────────────────
function buildScatter() {
  const el = document.getElementById('scatter-container');
  const W = el.clientWidth, H = 440;
  const margin = { top: 30, right: 30, bottom: 50, left: 50 };
  const iW = W - margin.left - margin.right;
  const iH = H - margin.top - margin.bottom;

  const svg = d3.select('#scatter-container').append('svg')
    .attr('width', W).attr('height', H)
    .append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const valid = DATA.countries.filter(c => c.log_gdp != null && c.lp != null);
  const xScale = d3.scaleLinear().domain(d3.extent(valid, d => d.log_gdp)).nice().range([0, iW]);
  const yScale = d3.scaleLinear().domain([0, 105]).range([iH, 0]);

  // 회귀선
  const xMean = d3.mean(valid, d => d.log_gdp);
  const yMean = d3.mean(valid, d => d.lp);
  const num = d3.sum(valid, d => (d.log_gdp - xMean) * (d.lp - yMean));
  const den = d3.sum(valid, d => (d.log_gdp - xMean) ** 2);
  const slope = num / den, intercept = yMean - slope * xMean;
  const xExt = d3.extent(valid, d => d.log_gdp);

  // 위/아래 영역 텍스트
  svg.append('text').attr('x', iW - 10).attr('y', 16)
    .attr('text-anchor', 'end').attr('fill', 'rgba(251,113,133,0.55)').attr('font-size', 11).attr('font-weight', 700)
    .text('▲ 기대보다 부진한 영역 (위기 국가)');
  svg.append('text').attr('x', iW - 10).attr('y', iH - 8)
    .attr('text-anchor', 'end').attr('fill', 'rgba(56,189,248,0.55)').attr('font-size', 11).attr('font-weight', 700)
    .text('▼ 기대보다 우수한 영역 (기적의 국가)');

  // 회귀선
  svg.append('line')
    .attr('x1', xScale(xExt[0])).attr('y1', yScale(intercept + slope * xExt[0]))
    .attr('x2', xScale(xExt[1])).attr('y2', yScale(intercept + slope * xExt[1]))
    .attr('stroke', '#4f8ef7').attr('stroke-width', 1.5).attr('stroke-dasharray', '6,4').attr('opacity', 0.7);

  const colorOf = g => g === 'positive' ? '#38bdf8' : g === 'negative' ? '#fb7185' : '#4a5568';
  const korNameMap = {
    'Sri Lanka': '스리랑카', 'Viet Nam': '베트남', 'Albania': '알바니아',
    'Benin': '베냉', 'Serbia': '세르비아'
  };

  const tooltip = document.getElementById('map-tooltip');
  svg.selectAll('circle').data(valid).join('circle')
    .attr('cx', d => xScale(d.log_gdp)).attr('cy', d => yScale(d.lp))
    .attr('r', d => d.deviance_group !== 'middle' ? 6 : 4)
    .attr('fill', d => colorOf(d.deviance_group))
    .attr('opacity', d => d.deviance_group !== 'middle' ? 0.9 : 0.35)
    .attr('stroke', d => d.deviance_group !== 'middle' ? 'white' : 'none')
    .attr('stroke-width', 1)
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', 9);
      const korName = korNameMap[d.name] || d.name;
      tooltip.innerHTML = `<strong>${korName}</strong><br>Learning Poverty: ${d.lp?.toFixed(1)}%<br>GDP (1인당): $${Math.round(d.gdp || 0).toLocaleString()}`;
      tooltip.classList.remove('hidden');
      positionTooltip(event, tooltip);
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', d.deviance_group !== 'middle' ? 6 : 4);
      tooltip.classList.add('hidden');
    });

  // TOP5 라벨
  const top5Names = (DATA.top_deviants || []).map(d => d.country);
  valid.filter(c => top5Names.includes(c.name)).forEach(c => {
    svg.append('text')
      .attr('x', xScale(c.log_gdp) + 9).attr('y', yScale(c.lp) + 4)
      .attr('fill', '#38bdf8').attr('font-size', 11).attr('font-weight', 700)
      .text(korNameMap[c.name] || c.name);
  });

  svg.append('g').attr('transform', `translate(0,${iH})`)
    .call(d3.axisBottom(xScale).ticks(0)).selectAll('text').remove();
  svg.append('g').call(d3.axisLeft(yScale).ticks(6).tickFormat(d => d + '%'))
    .selectAll('text').style('fill', '#a8b5d0').style('font-size', '10px');
  svg.selectAll('.domain, .tick line').attr('stroke', 'rgba(255,255,255,0.1)');

  svg.append('text').attr('x', iW / 2).attr('y', iH + 30)
    .attr('text-anchor', 'middle').attr('fill', '#6b7a99').attr('font-size', 11)
    .text('GDP (1인당 소득) 증가 방향 ➡');
  svg.append('text').attr('transform', 'rotate(-90)').attr('x', -iH / 2).attr('y', -38)
    .attr('text-anchor', 'middle').attr('fill', '#6b7a99').attr('font-size', 11)
    .text('Learning Poverty율 (%)');
}

// ── TOP 5 카드 ─────────────────────────────────────────
function buildTop5() {
  const container = document.getElementById('top5-cards');
  if (!DATA.top_deviants) return;
  const korNames = {
    'Sri Lanka': '스리랑카', 'Viet Nam': '베트남', 'Albania': '알바니아',
    'Benin': '베냉', 'Serbia': '세르비아'
  };

  container.innerHTML = DATA.top_deviants.map(d => `
    <div class="top5-card">
      <div class="top5-rank">#${d.rank}</div>
      <div class="top5-info">
        <div class="top5-country">${korNames[d.country] || d.country}</div>
        <div class="top5-detail">예측보다 약 ${Math.abs(d.residual).toFixed(0)}%p 낮은 Learning Poverty 달성</div>
      </div>
    </div>
  `).join('');
}

// ── Cohen's d 막대 차트 ────────────────────────────────
function buildCohensD() {
  const factors = [...DATA.a1_factors].sort((a, b) => Math.abs(a.cohens_d) - Math.abs(b.cohens_d));
  const labels = factors.map(f => f.label);
  const vals   = factors.map(f => Math.abs(f.cohens_d));
  const colors = factors.map(f => {
    if (!f.significant) return 'rgba(127,140,141,0.5)';
    return f.cohens_d < 0 ? '#fb7185' : '#38bdf8';
  });

  new Chart(document.getElementById('cohensDChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: '효과 크기(Cohen\'s d)', data: vals, backgroundColor: colors, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const f = factors[ctx.dataIndex];
              if (!f.significant) return `통계적으로 비유의 (p=${f.p_value.toFixed(2)})`;
              const dir = f.cohens_d < 0 ? '우수 국가가 더 낮음' : '우수 국가가 더 높음';
              return `효과 크기: ${Math.abs(f.cohens_d).toFixed(2)} — ${dir} (p=${f.p_value.toFixed(4)})`;
            }
          }
        }
      },
      scales: {
        x: { min: 0, max: 1.5, ticks: { color: '#a8b5d0', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font: { size: 11 } }, grid: { display: false } }
      }
    }
  });
}

// ── 분위별 히트맵 ──────────────────────────────────────
function buildQuartileHeatmap() {
  const el = document.getElementById('quartile-heatmap');
  const data = DATA.a1_quartile || [];
  if (!data.length) return;

  const quarters = ['최저소득국', '저소득국', '중소득국', '고소득국'];
  const data_quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
  const labels = [...new Set(data.map(d => d.label))];
  const lookup = {};
  data.forEach(d => { lookup[`${d.label}_${d.quartile}`] = d; });

  const thead = `<thead><tr><th>요인</th>${quarters.map(q => `<th>${q}</th>`).join('')}</tr></thead>`;
  const tbody = '<tbody>' + labels.map(label => {
    const cells = data_quarters.map(q => {
      const d = lookup[`${label}_${q}`];
      if (!d) return `<td class="heatmap-empty">—</td>`;
      const absVal = Math.abs(d.cohens_d);
      if (absVal > 1.0) return `<td style="background:rgba(79,142,247,0.45);color:#fff;padding:10px 6px;font-weight:700;">매우 중요</td>`;
      if (absVal > 0.5) return `<td style="background:rgba(79,142,247,0.18);color:#a8b5d0;padding:10px 6px;">중요</td>`;
      return `<td class="heatmap-empty" style="padding:10px 6px;">—</td>`;
    });
    return `<tr><td class="heatmap-label" style="padding:10px;border-right:1px solid rgba(255,255,255,0.08);">${label}</td>${cells.join('')}</tr>`;
  }).join('') + '</tbody>';

  el.innerHTML = `<table class="heatmap-table" style="width:100%;border-collapse:collapse;text-align:center;">${thead}${tbody}</table>`;
}

// ── A2 회귀 계수 차트 ──────────────────────────────────
function buildA2Charts() {
  // 차트 렌더링 로직 제거: index.html에서 메트릭 카드로 대체되었습니다.
}

// ── 정책 제언 카드 ─────────────────────────────────────
function buildPolicyCards() {
  const grid = document.getElementById('policy-grid');
  const evidenceMap = {
    1: '10대 출산율: Cohen\'s d = -0.92, p = 0.0001 — 가장 강력한 독립 성공요인',
    2: '의사 수: d = +0.78 / 교사-학생 비율: d = -0.68 — 교육지출(p=0.49)은 비유의',
    3: '거버넌스 β = -16.6, p < 0.001 — GDP 통제 후에도 16.6%p 감소',
    4: 'TOP 5 국가 평균 29%p 개선 — 스리랑카·베트남·베냉 모범 사례'
  };

  grid.innerHTML = DATA.policy_recommendations.map(p => `
    <div class="policy-card">
      <div class="policy-number">ACTION 0${p.id}</div>
      <div class="policy-icon">${p.icon}</div>
      <div class="policy-title">${p.title}</div>
      <div class="policy-subtitle">${p.subtitle}</div>
      <div class="policy-headline">${p.headline}</div>
      <div class="policy-evidence">📊 ${evidenceMap[p.id] || '데이터 분석으로 확인된 핵심 요인'}</div>
      <div class="policy-actions">
        ${p.actions.map(a => `<div class="policy-action">${a}</div>`).join('')}
      </div>
    </div>
  `).join('');
}

// ── 스크롤 reveal ──────────────────────────────────────
function setupReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

document.addEventListener('DOMContentLoaded', init);
