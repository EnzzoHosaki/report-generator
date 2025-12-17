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
      series: [{ name: 'Total Ativos', data: rawData.ativos?.total || [] }],
      chart: { type: 'line', height: 250 },
      xaxis: { categories: rawData.meses || [] },
      yaxis: { labels: { formatter: (val) => `R$ ${val}k` } }
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
function openPeriodFilters() {
  loadBranches();
  document.getElementById('periodFilterModal').classList.add('active');
}

function closePeriodFilters() {
  document.getElementById('periodFilterModal').classList.remove('active');
  // Fechar dropdowns ao fechar modal
  document.getElementById('monthsMenu').classList.remove('active');
  document.getElementById('branchesMenu').classList.remove('active');
  document.querySelector('#monthsDropdown .dropdown-toggle').classList.remove('active');
  document.querySelector('#branchesDropdown .dropdown-toggle').classList.remove('active');
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
  checkbox.checked = !checkbox.checked;
  updateMonthsLabel();
}

function updateMonthsLabel() {
  const checkboxes = document.querySelectorAll('[id^="month"]:checked');
  const count = checkboxes.length;
  const label = document.getElementById('monthsLabel');

  if (count === 0) {
    label.textContent = 'Nenhum mês selecionado';
  } else if (count === 12) {
    label.textContent = 'Todos os meses (12)';
  } else {
    label.textContent = `${count} ${count === 1 ? 'mês selecionado' : 'meses selecionados'}`;
  }
}

function selectAllMonths() {
  for (let i = 1; i <= 12; i++) {
    document.getElementById('month' + i).checked = true;
  }
  updateMonthsLabel();
}

function clearAllMonths() {
  for (let i = 1; i <= 12; i++) {
    document.getElementById('month' + i).checked = false;
  }
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
  checkbox.checked = !checkbox.checked;
  updateBranchesLabel();
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
  const clientId = window.location.pathname.split('/').pop();
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
        checkbox.checked = true;
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

  // Coletar meses selecionados
  const selectedMonths = [];
  for (let i = 1; i <= 12; i++) {
    const checkbox = document.getElementById('month' + i);
    if (checkbox.checked) {
      selectedMonths.push(checkbox.value);
    }
  }

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
  const clientId = window.location.pathname.split('/').pop();
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
