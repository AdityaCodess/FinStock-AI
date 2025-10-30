// finstock-ai/frontend/js/main.js

document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const WS_BASE_URL = 'ws://127.0.0.1:8000/ws';

    const searchInput = document.getElementById('stock-search');
    const searchResults = document.getElementById('search-results');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    let intradaySocket = null;
    let searchTimer;
    let currentSelectedSymbol = null;

    // --- Initialize Tab Widgets ---
    setupTabs('widget-ai-predictions');
    setupTabs('widget-news');
    
    // --- Set default dates ---
    function setDefaultDates() {
        const today = new Date();
        const fiveYearsAgo = new Date(today.getFullYear() - 5, today.getMonth(), today.getDate());
        endDateInput.value = today.toISOString().split('T')[0];
        startDateInput.value = fiveYearsAgo.toISOString().split('T')[0];
    }
    setDefaultDates();

    // --- Search Bar Logic ---
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        clearTimeout(searchTimer);
        currentSelectedSymbol = null;

        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }

        searchTimer = setTimeout(() => {
            fetchSearchQuery(query);
        }, 300);
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            searchResults.style.display = 'none';
            const symbolToAnalyze = currentSelectedSymbol || searchInput.value.trim().toUpperCase();
            
            if (symbolToAnalyze) {
                 currentSelectedSymbol = symbolToAnalyze.split(' ')[0];
                 console.log(`Analyzing (Enter): ${currentSelectedSymbol}`);
                 fetchFullAnalysis(currentSelectedSymbol);
                 connectWebSocket(currentSelectedSymbol);
            }
        }
    });


    async function fetchSearchQuery(query) {
        try {
            const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search network response was not ok');
            const data = await response.json();
            displaySearchResults(data);
        } catch (error) {
            console.error('Search fetch error:', error);
            searchResults.innerHTML = '<div class="search-result-item">Error fetching results.</div>';
            searchResults.style.display = 'block';
        }
    }

    function displaySearchResults(stocks) {
        searchResults.innerHTML = '';
        if (!stocks || stocks.length === 0) {
            searchResults.innerHTML = '<div class="search-result-item">No results found.</div>';
            searchResults.style.display = 'block';
            return;
        }

        stocks.forEach(stock => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.innerHTML = `<strong>${stock.symbol}</strong> <span>${stock.name}</span>`;
            item.addEventListener('click', () => selectStock(stock));
            searchResults.appendChild(item);
        });

        searchResults.style.display = 'block';
    }

    function selectStock(stock) {
        if (!stock || !stock.symbol) return;
        
        searchInput.value = `${stock.name} (${stock.symbol})`;
        currentSelectedSymbol = stock.symbol;
        searchResults.style.display = 'none';

        fetchFullAnalysis(stock.symbol);
        connectWebSocket(stock.symbol);
    }

    document.addEventListener('click', (e) => {
        if (searchInput && searchResults && !searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    startDateInput.addEventListener('change', handleDateChange);
    endDateInput.addEventListener('change', handleDateChange);

    function handleDateChange() {
        if (currentSelectedSymbol) {
            console.log(`Date changed, re-fetching data for ${currentSelectedSymbol}`);
            fetchFullAnalysis(currentSelectedSymbol);
        }
    }

    // --- Main Analysis Fetch ---
    async function fetchFullAnalysis(symbol) {
        if (!symbol) return;
        
        showLoader();
        
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        let url = `${API_BASE_URL}/analyze?symbol=${encodeURIComponent(symbol)}`;
        if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
        if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
        
        console.log(`Fetching: ${url}`);
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: `Analysis fetch failed: ${response.status}` }));
                throw new Error(errData.detail || `Analysis fetch failed: ${response.status}`);
            }
            const data = await response.json();
            if (!data) throw new Error("Received empty data from analysis endpoint.");

            if (data.stock_info) updateStockInfo(data.stock_info);
            if (data.statistics) updateStatistics(data.statistics);
            if (data.ai_predictions) updateAIPredictions(data.ai_predictions);
            if (data.news_sentiment) updateNews(data.news_sentiment);
            if (data.historical_data) createOrUpdatePriceChart(data.historical_data);
            if (data.daily_returns_histogram) createOrUpdateReturnHistogram(data.daily_returns_histogram);

        } catch (error) {
            console.error('Full analysis fetch error:', error);
            alert(`Error fetching analysis: ${error.message}`);
            // FIXED: Removed the broken call to destroyAllCharts()
        } finally {
            hideLoader();
        }
    }

    // --- WebSocket Connection ---
    function connectWebSocket(symbol) {
        if (intradaySocket && intradaySocket.readyState !== WebSocket.CLOSED) {
            console.log("Closing previous WebSocket connection.");
            intradaySocket.onclose = null;
            intradaySocket.close();
        }

        const wsUrl = `${WS_BASE_URL}/intraday?symbol=${encodeURIComponent(symbol)}`;
        console.log("Connecting to WebSocket:", wsUrl);
        intradaySocket = new WebSocket(wsUrl);

        intradaySocket.onopen = (event) => {
            console.log("WebSocket connection opened for:", symbol);
        };

        intradaySocket.onmessage = (event) => {
             try {
                const message = JSON.parse(event.data);
                if (message.type === 'intraday_update' && message.data) {
                    updateIntradayWidget(message.data);
                } else {
                     console.warn("Received unexpected WebSocket message format:", message);
                }
             } catch (e) {
                  console.error("Error parsing WebSocket message:", e, event.data);
             }
        };

        intradaySocket.onclose = (event) => {
            if (event.wasClean) console.log(`WebSocket closed cleanly`);
            else console.warn('WebSocket connection died unexpectedly.');
            intradaySocket = null;
        };

        intradaySocket.onerror = (error) => {
            console.error("WebSocket error:", error);
            intradaySocket = null;
        };
    }
});