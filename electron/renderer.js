const statusEl = document.getElementById('status');
const jsonEl = document.getElementById('json');
const ctx = document.getElementById('speedChart').getContext('2d');

let chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'Mean Speed (px/s)',
      data: [],
      borderColor: 'blue',
      fill: false
    }]
  },
  options: {
    responsive: true,
    scales: { x: { display: false } }
  }
});

const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  statusEl.textContent = 'Connected to Python agent';
};

ws.onmessage = (msg) => {
  const data = JSON.parse(msg.data);
  jsonEl.textContent = JSON.stringify(data, null, 2);

  chart.data.labels.push(new Date(data.timestamp).toLocaleTimeString());
  chart.data.datasets[0].data.push(data.mean_speed);

  if (chart.data.labels.length > 50) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update();
};

ws.onclose = () => {
  statusEl.textContent = 'Disconnected from Python agent';
};
