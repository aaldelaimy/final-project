async function fetchSensorData(sensorType) {
    const response = await fetch(`/api/${sensorType}`);
    return await response.json();
}

function createChart(ctx, data, label, color) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.timestamp),
            datasets: [{
                label: label,
                data: data.map(d => d.value),
                borderColor: color,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Value'
                    }
                }
            }
        }
    });
}

async function initCharts() {
    // Temperature Chart
    const tempData = await fetchSensorData('temperature');
    const tempCtx = document.getElementById('temperatureChart').getContext('2d');
    createChart(tempCtx, tempData, 'Temperature (°C)', '#ff6384');

    // Humidity Chart
    const humidityData = await fetchSensorData('humidity');
    const humidityCtx = document.getElementById('humidityChart').getContext('2d');
    createChart(humidityCtx, humidityData, 'Humidity (%)', '#36a2eb');

    // Light Chart
    const lightData = await fetchSensorData('light');
    const lightCtx = document.getElementById('lightChart').getContext('2d');
    createChart(lightCtx, lightData, 'Light (lux)', '#ffce56');
}

initCharts();