/* === CONFIGURAÇÃO DE CORES E GRÁFICOS === */
const colors = {
  primary: '#2d5a3d',
  secondary: '#7fa88f',
  tertiary: '#1a1a1a',
  accent: '#d4af37',
  bg: '#fafbfa'
};

const commonOptions = {
  chart: {
    fontFamily: 'Inter, sans-serif',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeinout', speed: 800 }
  },
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 3 },
  colors: [colors.primary, colors.secondary, '#d1d9d0', colors.tertiary]
};

const rawData = window.reportData || {};

/* === FORMATAÇÃO COMPACTA DE VALORES (PT-BR) === */
function formatCompact(val) {
  if (val == null || isNaN(val)) return 'R$ 0';
  const abs = Math.abs(val);
  let num, suffix;
  if (abs >= 1e9) { num = val / 1e9; suffix = 'Bi'; }
  else if (abs >= 1e6) { num = val / 1e6; suffix = 'Mi'; }
  else if (abs >= 1e3) { num = val / 1e3; suffix = 'M'; }
  else { num = val; suffix = ''; }
  // No máximo 2 casas decimais, removendo zeros à direita
  let txt = num.toFixed(2).replace(/\.?0+$/, '');
  return `R$ ${txt}${suffix}`;
}

/* === RENDERIZAÇÃO DE GRÁFICOS === */
function renderCharts() {
  if (!rawData || Object.keys(rawData).length === 0) {
    console.warn('Dados de gráficos não disponíveis');
    return;
  }

  // Gráfico de Ativos - Evolução
  if (document.querySelector("#chart-ativos-evolucao")) {
    new ApexCharts(document.querySelector("#chart-ativos-evolucao"), {
      ...commonOptions,
      series: [{ name: 'Total Ativos', data: (rawData.ativos?.total || []).map(v => Math.round(v * 100) / 100) }],
      chart: { type: 'line', height: 250 },
      xaxis: { categories: rawData.meses || [] },
      yaxis: { labels: { formatter: formatCompact } },
      tooltip: { y: { formatter: formatCompact } }
    }).render();
  }

  // Gráfico de Ativos - Composição
  if (document.querySelector("#chart-ativos-composicao")) {
    new ApexCharts(document.querySelector("#chart-ativos-composicao"), {
      ...commonOptions,
      series: [
        { name: 'Caixa', data: rawData.ativos?.caixa || [] },
        { name: 'Estoques', data: rawData.ativos?.estoques || [] },
        { name: 'Imobilizado', data: rawData.ativos?.imobilizado || [] }
      ],
      chart: { type: 'bar', height: 250, stacked: true, stackType: '100%' },
      xaxis: { categories: rawData.meses || [] },
      plotOptions: { bar: { horizontal: false, borderRadius: 4 } }
    }).render();
  }

  // Gráfico de Passivos
  if (document.querySelector("#chart-passivos")) {
    new ApexCharts(document.querySelector("#chart-passivos"), {
      ...commonOptions,
      series: [
        { name: 'Não Circulante', data: rawData.passivos?.nao_circulante || [] },
        { name: 'Circulante', data: rawData.passivos?.circulante || [] }
      ],
      chart: { type: 'area', height: 250, stacked: true },
      colors: [colors.tertiary, colors.secondary],
      xaxis: { categories: rawData.meses || [] }
    }).render();
  }

  // Gráfico de Rentabilidade
  if (document.querySelector("#chart-rentabilidade")) {
    new ApexCharts(document.querySelector("#chart-rentabilidade"), {
      ...commonOptions,
      series: [
        { name: 'RPS', data: rawData.rentabilidade?.rps || [] },
        { name: 'CDI', data: rawData.rentabilidade?.cdi || [] }
      ],
      chart: { type: 'line', height: 250 },
      stroke: { dashArray: [0, 5] },
      xaxis: { categories: rawData.meses || [] },
      yaxis: { labels: { formatter: (val) => `${val}%` } }
    }).render();
  }

  // Gráfico de Equity
  if (document.querySelector("#chart-equity")) {
    new ApexCharts(document.querySelector("#chart-equity"), {
      ...commonOptions,
      series: [
        { name: 'Patrimônio Líquido', data: rawData.rentabilidade?.pl || [] },
        { name: 'Ativos Totais', data: rawData.rentabilidade?.ativos || [] }
      ],
      chart: { type: 'line', height: 250 },
      xaxis: { categories: rawData.meses || [] }
    }).render();
  }

  // Gráfico de Top Faturamento
  if (document.querySelector("#chart-top-fat")) {
    new ApexCharts(document.querySelector("#chart-top-fat"), {
      ...commonOptions,
      series: [{ name: 'Faturamento', data: rawData.produtos?.fat_values || [] }],
      chart: { type: 'bar', height: 250 },
      plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
      xaxis: { categories: rawData.produtos?.fat_labels || [] },
      colors: [colors.primary]
    }).render();
  }

  // Gráfico de Top Quantidade
  if (document.querySelector("#chart-top-qtd")) {
    new ApexCharts(document.querySelector("#chart-top-qtd"), {
      ...commonOptions,
      series: [{ name: 'Quantidade', data: rawData.produtos?.qtd_values || [] }],
      chart: { type: 'bar', height: 250 },
      plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
      xaxis: { categories: rawData.produtos?.qtd_labels || [] },
      colors: [colors.secondary]
    }).render();
  }

  // Gráfico de Vendas YoY
  if (document.querySelector("#chart-vendas-yoy")) {
    new ApexCharts(document.querySelector("#chart-vendas-yoy"), {
      ...commonOptions,
      series: [
        { name: '2024', data: rawData.vendas?.atual || [] },
        { name: '2023', data: rawData.vendas?.anterior || [] }
      ],
      chart: { type: 'line', height: 200 },
      xaxis: { categories: rawData.meses || [] }
    }).render();
  }

  // Gráfico de Custos
  if (document.querySelector("#chart-custos")) {
    new ApexCharts(document.querySelector("#chart-custos"), {
      ...commonOptions,
      series: rawData.custos?.values || [],
      labels: rawData.custos?.labels || [],
      chart: { type: 'donut', height: 250 },
      colors: [colors.primary, colors.secondary, '#d8e2d8', colors.tertiary]
    }).render();
  }

  // Gráfico de Fornecedores
  if (document.querySelector("#chart-fornecedores")) {
    new ApexCharts(document.querySelector("#chart-fornecedores"), {
      ...commonOptions,
      series: rawData.fornecedores?.values || [],
      labels: rawData.fornecedores?.labels || [],
      chart: { type: 'donut', height: 250 },
      colors: [colors.primary, colors.secondary, '#d8e2d8']
    }).render();
  }
}

document.addEventListener('DOMContentLoaded', renderCharts);

/* === GERAR QR CODE === */
document.addEventListener('DOMContentLoaded', function () {
  const clientId = window.location.pathname.split('/').pop();
  const periodo = new URLSearchParams(window.location.search).get('periodo') || '';
  const pdfUrl = `${window.location.origin}/report/pdf/${clientId}?periodo=${encodeURIComponent(periodo)}`;

  try {
    QRCode.toCanvas(document.getElementById('qrCodeContainer'), pdfUrl, {
      width: 200,
      margin: 1,
      color: {
        dark: '#2d5a3d',
        light: '#ffffff'
      }
    }, function (error) {
      if (error) console.error('Erro ao gerar QR code:', error);
    });
  } catch (e) {
    console.log('QR Code não disponível em modo PDF');
  }
});

/* === NAVEGAÇÃO E SCROLL SPY === */
const pageIds = ['capa', 'resumo', 'ativos', 'passivos', 'custos', 'rentabilidade', 'vendas', 'tributario', 'distribuicao', 'conclusao', 'agradecimentos'];
let currentIndex = 0;

function goToSlide(id) {
  document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

// Scroll Spy & Atualização do Índice
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // Atualiza menu lateral
      document.querySelectorAll('.nav-dot-container').forEach(el => el.classList.remove('active'));
      const navId = 'nav-' + entry.target.id;
      const navItem = document.getElementById(navId);
      if (navItem) navItem.classList.add('active');

      // Atualiza índice atual
      currentIndex = pageIds.indexOf(entry.target.id);
    }
  });
}, { root: document.getElementById('mainScroll'), threshold: 0.5 });

document.querySelectorAll('.page-container').forEach(page => observer.observe(page));

// Navegação Sequencial
function nextSlide() {
  if (currentIndex < pageIds.length - 1) {
    goToSlide(pageIds[currentIndex + 1]);
  }
}

function prevSlide() {
  if (currentIndex > 0) {
    goToSlide(pageIds[currentIndex - 1]);
  }
}

// Controle por Teclado
document.addEventListener('keydown', (e) => {
  if (e.key === "ArrowDown" || e.key === "ArrowRight") {
    e.preventDefault();
    nextSlide();
  } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
    e.preventDefault();
    prevSlide();
  }
});

/* === TOGGLE FULLSCREEN === */
let hideControlsTimer = null;

function toggleFullScreen() {
  if (!document.fullscreenElement) {
    document.body.classList.add('fullscreen-mode');
    document.documentElement.requestFullscreen().catch(err => console.log(err));
    startHideControlsTimer();
  } else {
    document.exitFullscreen();
    document.body.classList.remove('fullscreen-mode');
    clearHideControlsTimer();
  }
}

document.addEventListener('fullscreenchange', () => {
  if (!document.fullscreenElement) {
    document.body.classList.remove('fullscreen-mode');
    clearHideControlsTimer();
  }
});

// Gerenciar ocultação de controles após inatividade
function startHideControlsTimer() {
  // Mostrar controles imediatamente
  document.body.classList.remove('hide-controls');

  // Limpar timer anterior se existir
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
  }

  // Iniciar novo timer para ocultar após 200ms
  hideControlsTimer = setTimeout(() => {
    if (document.body.classList.contains('fullscreen-mode')) {
      document.body.classList.add('hide-controls');
    }
  }, 200);
}

function clearHideControlsTimer() {
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
  document.body.classList.remove('hide-controls');
}

// Detectar movimento do mouse apenas em fullscreen
document.addEventListener('mousemove', (e) => {
  if (document.body.classList.contains('fullscreen-mode')) {
    startHideControlsTimer();
  }
});

// Ao clicar, também resetar o timer
document.addEventListener('click', (e) => {
  if (document.body.classList.contains('fullscreen-mode')) {
    startHideControlsTimer();
  }
});

/* === FUNÇÕES PARA FILTROS DE PERÍODO === */

// Nomes dos meses em português
const MESES_NOMES = {
  1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
  5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
  9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
};

// Anos disponíveis (fixos)
const ANOS_DISPONIVEIS = [2026, 2025, 2024, 2023];

function getClientId() {
  return window.location.pathname.split('/').pop();
}

function getCurrentUrlParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    year: params.get('year') ? parseInt(params.get('year')) : null,
    months: params.get('months') ? params.get('months').split(',').map(m => parseInt(m)) : null,
    branches: params.get('branches') ? params.get('branches').split(',').map(b => parseInt(b)) : null
  };
}

function getMesAtual() {
  return new Date().getMonth() + 1; // getMonth() retorna 0-11
}

function getAnoAtual() {
  return new Date().getFullYear();
}

function openPeriodFilters() {
  document.getElementById('periodFilterModal').classList.add('active');
  loadYearsAndMonths();
  loadBranches();
}

function closePeriodFilters() {
  document.getElementById('periodFilterModal').classList.remove('active');
  // Fechar dropdowns ao fechar modal
  document.getElementById('monthsMenu').classList.remove('active');
  document.getElementById('branchesMenu').classList.remove('active');
  document.querySelector('#monthsDropdown .dropdown-toggle').classList.remove('active');
  document.querySelector('#branchesDropdown .dropdown-toggle').classList.remove('active');
}

/* === CARREGAMENTO DE ANOS E MESES (FIXOS) === */
function loadYearsAndMonths() {
  const urlParams = getCurrentUrlParams();
  const yearSelect = document.getElementById('filterYear');
  yearSelect.innerHTML = '';
  
  const anoAtual = getAnoAtual();
  
  ANOS_DISPONIVEIS.forEach((ano, index) => {
    const option = document.createElement('option');
    option.value = ano;
    option.textContent = ano;
    // Selecionar o ano da URL ou o ano atual
    if (urlParams.year && urlParams.year === ano) {
      option.selected = true;
    } else if (!urlParams.year && ano === anoAtual) {
      option.selected = true;
    }
    yearSelect.appendChild(option);
  });
  
  // Carregar meses do ano selecionado
  const selectedYear = parseInt(yearSelect.value);
  loadMesesParaAno(selectedYear, urlParams.months);
}

function onYearChange() {
  const yearSelect = document.getElementById('filterYear');
  const selectedYear = parseInt(yearSelect.value);
  loadMesesParaAno(selectedYear, null); // null = selecionar todos os meses disponíveis
}

function loadMesesParaAno(ano, mesesPreSelecionados) {
  const container = document.getElementById('monthsMenuItems');
  container.innerHTML = '';
  
  const anoAtual = getAnoAtual();
  const mesAtual = getMesAtual();
  
  // Se for o ano atual, mostrar apenas até o mês atual
  const mesMaximo = (ano === anoAtual) ? mesAtual : 12;
  
  for (let mes = 1; mes <= mesMaximo; mes++) {
    const div = document.createElement('div');
    div.className = 'dropdown-item';
    div.onclick = () => toggleMonthCheckbox(mes);

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `month${mes}`;
    checkbox.value = mes;
    // Se há meses pré-selecionados (da URL), usa eles; senão, marca todos
    checkbox.checked = mesesPreSelecionados ? mesesPreSelecionados.includes(mes) : true;
    checkbox.onclick = (e) => {
      e.stopPropagation();
      updateMonthsLabel();
    };

    const label = document.createElement('label');
    label.htmlFor = `month${mes}`;
    label.textContent = MESES_NOMES[mes];
    label.onclick = (e) => e.stopPropagation();

    div.appendChild(checkbox);
    div.appendChild(label);
    container.appendChild(div);
  }
  
  updateMonthsLabel();
}

/* === DROPDOWN DE MESES === */
function toggleMonthsDropdown() {
  const menu = document.getElementById('monthsMenu');
  const toggle = document.querySelector('#monthsDropdown .dropdown-toggle');
  const branchesMenu = document.getElementById('branchesMenu');
  const branchesToggle = document.querySelector('#branchesDropdown .dropdown-toggle');

  // Fechar dropdown de filiais se estiver aberto
  branchesMenu.classList.remove('active');
  branchesToggle.classList.remove('active');

  menu.classList.toggle('active');
  toggle.classList.toggle('active');
}

function toggleMonthCheckbox(monthNum) {
  const checkbox = document.getElementById('month' + monthNum);
  if (checkbox) {
    checkbox.checked = !checkbox.checked;
    updateMonthsLabel();
  }
}

function updateMonthsLabel() {
  const checkboxes = document.querySelectorAll('#monthsMenuItems input[type="checkbox"]:checked');
  const total = document.querySelectorAll('#monthsMenuItems input[type="checkbox"]').length;
  const count = checkboxes.length;
  const label = document.getElementById('monthsLabel');

  if (count === 0) {
    label.textContent = 'Nenhum mês selecionado';
  } else if (count === total && total > 0) {
    label.textContent = `Todos os meses (${total})`;
  } else {
    label.textContent = `${count} ${count === 1 ? 'mês selecionado' : 'meses selecionados'}`;
  }
}

function selectAllMonths() {
  document.querySelectorAll('#monthsMenuItems input[type="checkbox"]').forEach(cb => cb.checked = true);
  updateMonthsLabel();
}

function clearAllMonths() {
  document.querySelectorAll('#monthsMenuItems input[type="checkbox"]').forEach(cb => cb.checked = false);
  updateMonthsLabel();
}

/* === DROPDOWN DE FILIAIS === */
function toggleBranchesDropdown() {
  const menu = document.getElementById('branchesMenu');
  const toggle = document.querySelector('#branchesDropdown .dropdown-toggle');
  const monthsMenu = document.getElementById('monthsMenu');
  const monthsToggle = document.querySelector('#monthsDropdown .dropdown-toggle');

  // Fechar dropdown de meses se estiver aberto
  monthsMenu.classList.remove('active');
  monthsToggle.classList.remove('active');

  menu.classList.toggle('active');
  toggle.classList.toggle('active');
}

function toggleBranchCheckbox(branchId) {
  const checkbox = document.getElementById('branch' + branchId);
  if (checkbox) {
    checkbox.checked = !checkbox.checked;
    updateBranchesLabel();
  }
}

function updateBranchesLabel() {
  const checkboxes = document.querySelectorAll('[id^="branch"]:checked');
  const count = checkboxes.length;
  const label = document.getElementById('branchesLabel');
  const total = document.querySelectorAll('[id^="branch"]').length;

  if (count === 0) {
    label.textContent = 'Nenhuma filial selecionada';
  } else if (count === total) {
    label.textContent = `Todas as filiais (${total})`;
  } else {
    label.textContent = `${count} ${count === 1 ? 'filial selecionada' : 'filiais selecionadas'}`;
  }
}

function selectAllBranches() {
  document.querySelectorAll('[id^="branch"]').forEach(cb => cb.checked = true);
  updateBranchesLabel();
}

function clearAllBranches() {
  document.querySelectorAll('[id^="branch"]').forEach(cb => cb.checked = false);
  updateBranchesLabel();
}

function loadBranches() {
  const clientId = getClientId();
  const urlParams = getCurrentUrlParams();
  
  fetch(`/api/branches/${clientId}`)
    .then(response => response.json())
    .then(branches => {
      const container = document.getElementById('branchesMenuItems');
      container.innerHTML = '';

      if (branches.length === 0) {
        container.innerHTML = '<div style="padding: 12px; text-align: center; color: var(--text-secondary); font-size: 10pt;">Nenhuma filial encontrada</div>';
        document.getElementById('branchesLabel').textContent = 'Nenhuma filial disponível';
        return;
      }

      branches.forEach(branch => {
        const div = document.createElement('div');
        div.className = 'dropdown-item';
        div.onclick = () => toggleBranchCheckbox(branch.codigo);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `branch${branch.codigo}`;
        checkbox.value = branch.codigo;
        // Se há filiais pré-selecionadas na URL, usa elas; senão, marca todas
        checkbox.checked = urlParams.branches ? urlParams.branches.includes(branch.codigo) : true;
        checkbox.onclick = (e) => {
          e.stopPropagation();
          updateBranchesLabel();
        };

        const label = document.createElement('label');
        label.htmlFor = `branch${branch.codigo}`;
        label.textContent = `${branch.codigo} - ${branch.fantasia}`;
        label.onclick = (e) => e.stopPropagation();

        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
      });

      updateBranchesLabel();
    })
    .catch(error => {
      console.error('Erro ao carregar filiais:', error);
      const container = document.getElementById('branchesMenuItems');
      container.innerHTML = '<div style="padding: 12px; text-align: center; color: var(--danger-color); font-size: 10pt;">Erro ao carregar filiais</div>';
      document.getElementById('branchesLabel').textContent = 'Erro ao carregar';
    });
}

function applyPeriodFilter() {
  const year = document.getElementById('filterYear').value;
  
  if (!year) {
    alert('Selecione um ano!');
    return;
  }

  // Coletar meses selecionados
  const selectedMonths = [];
  document.querySelectorAll('#monthsMenuItems input[type="checkbox"]:checked').forEach(cb => {
    selectedMonths.push(cb.value);
  });

  if (selectedMonths.length === 0) {
    alert('Selecione pelo menos um mês!');
    return;
  }

  // Coletar filiais selecionadas
  const selectedBranches = [];
  document.querySelectorAll('[id^="branch"]:checked').forEach(cb => {
    selectedBranches.push(cb.value);
  });

  if (selectedBranches.length === 0) {
    alert('Selecione pelo menos uma filial!');
    return;
  }

  closePeriodFilters();

  // Construir parâmetros da URL
  const clientId = getClientId();
  const params = new URLSearchParams();
  params.set('year', year);
  params.set('months', selectedMonths.join(','));
  params.set('branches', selectedBranches.join(','));

  const queryString = params.toString();

  // Atualizar link do PDF com novos parâmetros
  document.getElementById('fabDownload').href = `/report/pdf/${clientId}?${queryString}`;

  // Redirecionar com os novos parâmetros
  window.location.href = `/report/view/${clientId}?${queryString}`;
}

// Fechar dropdowns ao clicar fora
document.addEventListener('click', (e) => {
  if (!e.target.closest('#monthsDropdown')) {
    document.getElementById('monthsMenu').classList.remove('active');
    document.querySelector('#monthsDropdown .dropdown-toggle')?.classList.remove('active');
  }
  if (!e.target.closest('#branchesDropdown')) {
    document.getElementById('branchesMenu').classList.remove('active');
    document.querySelector('#branchesDropdown .dropdown-toggle')?.classList.remove('active');
  }
});

// Fechar modal ao clicar fora
document.getElementById('periodFilterModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'periodFilterModal') closePeriodFilters();
});

/* === FUNÇÕES DO BALANCETE === */

let balanceteData = [];
let balanceteMode = 'empresa'; // 'empresa' (consolidado) ou 'filial'

function openBalancete() {
  const modal = document.getElementById('balanceteModal');
  if (!modal) return;
  modal.classList.add('active');
  
  document.getElementById('balanceteLoading').style.display = 'flex';
  document.getElementById('balanceteError').style.display = 'none';
  document.getElementById('balanceteTableWrapper').style.display = 'none';
  
  loadBalancete();
}

function closeBalancete() {
  const modal = document.getElementById('balanceteModal');
  if (modal) modal.classList.remove('active');
}

function loadBalancete() {
  const clientId = getClientId();
  const params = new URLSearchParams(window.location.search);
  
  // Usar os mesmos filtros já aplicados na URL
  const queryString = params.toString();
  const url = `/api/balancete/${clientId}${queryString ? '?' + queryString : ''}`;
  
  fetch(url)
    .then(response => {
      if (!response.ok) throw new Error('Erro na resposta');
      return response.json();
    })
    .then(data => {
      balanceteData = data.dados || [];
      // Reset toggle para modo empresa
      balanceteMode = 'empresa';
      document.getElementById('balanceteToggle').checked = false;
      updateToggleLabels();
      applyBalanceteView();
      
      document.getElementById('balanceteLoading').style.display = 'none';
      document.getElementById('balanceteTableWrapper').style.display = 'flex';
    })
    .catch(error => {
      console.error('Erro ao carregar balancete:', error);
      document.getElementById('balanceteLoading').style.display = 'none';
      document.getElementById('balanceteError').style.display = 'flex';
    });
}

function formatBRL(val) {
  if (val === null || val === undefined) val = 0;
  return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

const MESES_NOMES_BALANCETE = {
  1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
  5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
  9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
};

function consolidarPorEmpresa(dados) {
  const mapa = {};
  dados.forEach(row => {
    const chave = row.cod_conta_contabil;
    if (!mapa[chave]) {
      mapa[chave] = {
        cod_conta_contabil: row.cod_conta_contabil,
        nome_conta: row.nome_conta,
        tipo_conta: row.tipo_conta,
        natureza: row.natureza,
        cod_grupo: row.cod_grupo,
        saldo_inicial: 0,
        debito: 0,
        credito: 0,
        saldo: 0,
      };
    }
    mapa[chave].saldo_inicial += row.saldo_inicial || 0;
    mapa[chave].debito += row.debito || 0;
    mapa[chave].credito += row.credito || 0;
    mapa[chave].saldo += row.saldo || 0;
  });
  return Object.values(mapa).sort((a, b) => a.cod_conta_contabil.localeCompare(b.cod_conta_contabil));
}

function onBalanceteToggle() {
  const checked = document.getElementById('balanceteToggle').checked;
  balanceteMode = checked ? 'filial' : 'empresa';
  updateToggleLabels();
  applyBalanceteView();
}

function setBalanceteMode(mode) {
  balanceteMode = mode;
  document.getElementById('balanceteToggle').checked = (mode === 'filial');
  updateToggleLabels();
  applyBalanceteView();
}

function updateToggleLabels() {
  const lblEmpresa = document.getElementById('lblEmpresa');
  const lblFilial = document.getElementById('lblFilial');
  if (balanceteMode === 'empresa') {
    lblEmpresa.className = 'toggle-label-active';
    lblFilial.className = 'toggle-label-inactive';
  } else {
    lblEmpresa.className = 'toggle-label-inactive';
    lblFilial.className = 'toggle-label-active';
  }
}

function applyBalanceteView() {
  const dados = balanceteMode === 'empresa' ? consolidarPorEmpresa(balanceteData) : balanceteData;
  renderBalanceteTable(dados, balanceteMode);
  document.getElementById('balanceteCount').textContent = `${dados.length} registros encontrados`;
}

function renderBalanceteTable(dados, mode) {
  const thead = document.querySelector('#balanceteTable thead tr');
  const tbody = document.getElementById('balanceteBody');
  tbody.innerHTML = '';

  const isFilial = mode === 'filial';
  const colCount = isFilial ? 10 : 9;

  // Atualizar cabeçalho dinamicamente
  thead.innerHTML = `
    <th>Conta</th>
    <th>Nome da Conta</th>
    <th>Tipo</th>
    <th>Natureza</th>
    <th>Grupo</th>
    ${isFilial ? '<th>Filial</th>' : ''}
    <th class="text-right">Saldo Inicial</th>
    <th class="text-right">Débito</th>
    <th class="text-right">Crédito</th>
    <th class="text-right">Saldo</th>
  `;

  if (!dados || dados.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${colCount}" style="text-align:center; padding:30px; color:var(--text-secondary);">Nenhum dado encontrado para o período selecionado.</td></tr>`;
    return;
  }
  
  dados.forEach(row => {
    const tr = document.createElement('tr');
    if (row.tipo_conta === 'Sintetica') tr.classList.add('sintetica');
    
    const saldoClass = row.saldo >= 0 ? 'saldo-positivo' : 'saldo-negativo';
    
    tr.innerHTML = `
      <td>${row.cod_conta_contabil}</td>
      <td>${row.nome_conta}</td>
      <td>${row.tipo_conta}</td>
      <td>${row.natureza}</td>
      <td>${row.cod_grupo}</td>
      ${isFilial ? `<td>${row.nome_fantasia_filial || row.nome_filial || '-'}</td>` : ''}
      <td class="text-right">${formatBRL(row.saldo_inicial)}</td>
      <td class="text-right">${formatBRL(row.debito)}</td>
      <td class="text-right">${formatBRL(row.credito)}</td>
      <td class="text-right ${saldoClass}">${formatBRL(row.saldo)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function exportBalanceteCSV() {
  if (!balanceteData || balanceteData.length === 0) {
    alert('Nenhum dado para exportar.');
    return;
  }
  
  const exportData = balanceteMode === 'empresa' ? consolidarPorEmpresa(balanceteData) : balanceteData;
  const isFilial = balanceteMode === 'filial';
  
  const headers = isFilial
    ? ['Conta', 'Nome da Conta', 'Tipo', 'Natureza', 'Grupo', 'Filial', 'Saldo Inicial', 'Débito', 'Crédito', 'Saldo']
    : ['Conta', 'Nome da Conta', 'Tipo', 'Natureza', 'Grupo', 'Saldo Inicial', 'Débito', 'Crédito', 'Saldo'];
  const rows = exportData.map(r => {
    const base = [
      r.cod_conta_contabil,
      `"${(r.nome_conta || '').replace(/"/g, '""')}"`,
      r.tipo_conta,
      r.natureza,
      r.cod_grupo,
    ];
    if (isFilial) {
      base.push(`"${(r.nome_fantasia_filial || r.nome_filial || '').replace(/"/g, '""')}"`);
    }
    base.push(
      (r.saldo_inicial || 0).toFixed(2).replace('.', ','),
      (r.debito || 0).toFixed(2).replace('.', ','),
      (r.credito || 0).toFixed(2).replace('.', ','),
      (r.saldo || 0).toFixed(2).replace('.', ',')
    );
    return base;
  });
  
  const csvContent = '\uFEFF' + headers.join(';') + '\n' + rows.map(r => r.join(';')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `balancete_${getClientId()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// Fechar modal do balancete ao clicar fora
document.getElementById('balanceteModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'balanceteModal') closeBalancete();
});