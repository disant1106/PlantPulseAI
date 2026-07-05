const data = window.dashboardData || { severity: {}, issues: [] };

function chartDefaults() {
  Chart.defaults.color = "#9db7aa";
  Chart.defaults.borderColor = "rgba(171, 255, 213, 0.14)";
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
}

function makeSeverityChart() {
  const ctx = document.querySelector("#severityChart");
  if (!ctx) return;
  const labels = Object.keys(data.severity);
  const values = Object.values(data.severity);
  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: ["#47e58f", "#f6c35b", "#ff6f6f", "#72d2ff"],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } }
    }
  });
}

function makeIssuesChart() {
  const ctx = document.querySelector("#issuesChart");
  if (!ctx) return;
  const labels = data.issues.map(item => item.probable_issue);
  const values = data.issues.map(item => item.count);
  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Scans",
        data: values,
        backgroundColor: "#47e58f",
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      plugins: { legend: { display: false } }
    }
  });
}

if (window.Chart) {
  chartDefaults();
  makeSeverityChart();
  makeIssuesChart();
}
