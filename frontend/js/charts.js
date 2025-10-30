// finstock-ai/frontend/js/charts.js

let priceChart = null;
let histogramChart = null;

function destroyAllCharts() {
    destroyPriceChart();
    destroyHistogramChart();
}

function destroyPriceChart() {
    try {
        if (priceChart) {
            priceChart.destroy();
            priceChart = null;
            console.log("Price chart destroyed.");
        }
    } catch (e) {
        console.error("Error destroying price chart:", e);
        priceChart = null; // Ensure it's nulled
    }
}

function destroyHistogramChart() {
     try {
        if (histogramChart) {
            histogramChart.destroy();
            histogramChart = null;
            console.log("Histogram chart destroyed.");
        }
     } catch (e) {
         console.error("Error destroying histogram chart:", e);
         histogramChart = null;
     }
}

function createOrUpdatePriceChart(historicalData) {
    const canvas = document.getElementById('priceHistoryChart');
    if (!canvas) {
         console.error("Canvas element #priceHistoryChart not found!");
         return;
    }
    const ctx = canvas.getContext('2d');
    destroyPriceChart(); // Destroy existing chart first

    if (!historicalData || historicalData.length === 0) {
        console.warn("No historical data available for price chart.");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'var(--text-secondary)';
        ctx.textAlign = 'center'; ctx.font = '16px sans-serif';
        ctx.fillText('No historical data available.', canvas.width / 2, canvas.height / 2);
        return;
    }

    // --- THIS IS THE FIX ---
    // Use 'category' type and just pass the date strings as labels
    const labels = historicalData.map(point => point.date);
    const dataPoints = historicalData.map(point => point.close);
    // --- END FIX ---

    const data = {
        labels: labels, // Pass date strings as labels
        datasets: [{
            label: 'Closing Price', 
            data: dataPoints, // Pass closing prices
            borderColor: 'var(--accent-blue)', 
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            tension: 0.1, 
            pointRadius: 0, 
            fill: true, 
            borderWidth: 1.5
        }]
    };

    const config = {
        type: 'line', data: data,
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: {
                    // FIXED: Use 'category' axis. This is much more reliable than 'time'
                    type: 'category', 
                    ticks: { 
                        color: 'var(--text-secondary)', 
                        maxRotation: 0, 
                        autoSkip: true, 
                        maxTicksLimit: 8 // Show fewer labels
                    },
                    grid: { color: 'var(--border-color)' } // Brighter grid
                },
                y: {
                    beginAtZero: false,
                    ticks: {
                        color: 'var(--text-secondary)', padding: 10,
                        callback: value => '₹' + value.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
                    },
                     grid: { color: 'var(--border-color)' } // Brighter grid
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                   mode: 'index', intersect: false,
                   backgroundColor: 'rgba(30, 30, 30, 0.9)', titleColor: 'var(--text-primary)', bodyColor: 'var(--text-secondary)',
                   borderColor: 'var(--border-color)', borderWidth: 1, padding: 10,
                   callbacks: {
                        label: context => {
                             let label = context.dataset.label || '';
                             if (label) label += ': ';
                             if (context.parsed.y !== null) label += '₹' + context.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                             return label;
                        }
                    }
                }
            },
            animation: false, 
            parsing: false
        }
    };

    try {
        priceChart = new Chart(ctx, config);
        console.log("Price chart created/updated.");
    } catch (error) {
         console.error("Error creating price chart:", error);
         ctx.clearRect(0, 0, canvas.width, canvas.height);
         ctx.fillStyle = 'var(--accent-red)'; ctx.textAlign = 'center'; ctx.font = '16px sans-serif';
         ctx.fillText('Error creating price chart.', canvas.width / 2, canvas.height / 2);
    }
}

function createOrUpdateReturnHistogram(dailyReturns) {
    const canvas = document.getElementById('returnHistogramChart');
     if (!canvas) {
         console.error("Canvas element #returnHistogramChart not found!");
         return;
     }
    const ctx = canvas.getContext('2d');
    destroyHistogramChart();

    if (!dailyReturns || dailyReturns.length === 0) {
        console.warn("No daily returns data available for histogram.");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'var(--text-secondary)'; ctx.textAlign = 'center'; ctx.font = '14px sans-serif';
        ctx.fillText('No return data available.', canvas.width / 2, canvas.height / 2);
        return;
    }

    const minReturn = Math.min(...dailyReturns);
    const maxReturn = Math.max(...dailyReturns);
    const numBins = Math.min(20, Math.max(10, Math.ceil(Math.sqrt(dailyReturns.length) / 2)));
    const range = maxReturn - minReturn;
    const binWidth = range > 0 ? range / numBins : 1;

    const bins = Array(numBins).fill(0);
    const labels = Array(numBins);
    let binEdges = [];

    for (let i = 0; i < numBins; i++) {
        const binStart = minReturn + i * binWidth;
        const binEnd = (i === numBins - 1) ? maxReturn : binStart + binWidth;
        binEdges.push({ start: binStart, end: binEnd });
        labels[i] = `${binStart.toFixed(2)}%`;
    }

    dailyReturns.forEach(ret => {
        if (binWidth === 0) {
             if (ret === minReturn) bins[0]++;
             return;
        }
        let binIndex = Math.floor((ret - minReturn) / binWidth);
        binIndex = Math.max(0, Math.min(numBins - 1, binIndex));
        if (ret === maxReturn && binIndex < numBins -1) {
             binIndex = numBins - 1;
        }
        bins[binIndex]++;
    });

    const data = {
        labels: labels,
        datasets: [{
            label: 'Frequency', data: bins,
            backgroundColor: 'rgba(40, 167, 69, 0.7)',
            borderColor: 'rgba(40, 167, 69, 1)',
            borderWidth: 1, barPercentage: 1.0, categoryPercentage: 1.0
        }]
    };

    const config = {
        type: 'bar', data: data,
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        color: 'var(--text-secondary)', maxRotation: 45, minRotation: 30,
                        font: { size: 9 },
                        autoSkip: true,
                        maxTicksLimit: 8
                    },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                     title: { display: true, text: 'Frequency (Days)', color: 'var(--text-secondary)', font: { size: 11 } },
                    ticks: { color: 'var(--text-secondary)', precision: 0 },
                    grid: { color: 'var(--border-color)' } // Brighter grid
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index', intersect: false, backgroundColor: 'rgba(30, 30, 30, 0.9)',
                    titleColor: 'var(--text-primary)', bodyColor: 'var(--text-secondary)',
                    callbacks: {
                        title: function(tooltipItems) {
                             const index = tooltipItems[0].dataIndex;
                             if (binEdges[index]) {
                                 return `${binEdges[index].start.toFixed(2)}% to ${binEdges[index].end.toFixed(2)}%`;
                             }
                             return tooltipItems[0].label;
                        },
                        label: context => ` Days: ${context.parsed.y}`
                    }
                }
            },
            animation: false
        }
    };

    try {
        histogramChart = new Chart(ctx, config);
        console.log("Return histogram created/updated.");
    } catch (error) {
        console.error("Error creating histogram:", error);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'var(--accent-red)'; ctx.textAlign = 'center'; ctx.font = '14px sans-serif';
        ctx.fillText('Error creating histogram.', canvas.width / 2, canvas.height / 2);
    }
}