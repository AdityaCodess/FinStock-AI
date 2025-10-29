// finstock-ai/frontend/js/main.js

document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const WS_BASE_URL = 'ws://127.0.0.1:8000/ws'; // WebSocket URL

    const searchInput = document.getElementById('stock-search');
    const searchResults = document.getElementById('search-results');

    let intradaySocket = null; // WebSocket connection holder
    let searchTimer; // Timer for debouncing search input

    // --- Initialize Tab Widgets ---
    setupTabs('widget-ai-predictions');
    setupTabs('widget-news');

    // --- Search Bar Logic ---
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        clearTimeout(searchTimer);

        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }

        searchTimer = setTimeout(() => {
            fetchSearchQuery(query);
        }, 300); // Debounce API call
    });

    async function fetchSearchQuery(query) {
        try {
            const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Search network response was not ok: ${response.status} ${errorText}`);
            }
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
        if (!stock || !stock.symbol) {
             console.error("Invalid stock selected:", stock);
             return;
        }
        searchInput.value = `${stock.name} (${stock.symbol})`;
        searchResults.style.display = 'none';

        // Trigger the main analysis
        fetchFullAnalysis(stock.symbol);

        // Trigger the WebSocket connection
        // Note: WebSocket setup is now inside connectWebSocket
        connectWebSocket(stock.symbol);
    }

    // Hide search results if user clicks elsewhere
    document.addEventListener('click', (e) => {
        if (searchInput && searchResults && !searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    // --- Main Analysis Fetch ---
    async function fetchFullAnalysis(symbol) {
        showLoader();
        try {
            const response = await fetch(`${API_BASE_URL}/analyze?symbol=${encodeURIComponent(symbol)}`);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: `Analysis fetch failed: ${response.status}` })); // Handle non-JSON errors too
                throw new Error(errData.detail || `Analysis fetch failed: ${response.status}`);
            }
            const data = await response.json();

            if (!data) {
                throw new Error("Received empty data from analysis endpoint.");
            }

            // Populate the dashboard with the initial data
            if (data.stock_info) updateStockInfo(data.stock_info);
            if (data.statistics) updateStatistics(data.statistics);
            if (data.ai_predictions) updateAIPredictions(data.ai_predictions);
            if (data.news_sentiment) updateNews(data.news_sentiment);
            if (data.historical_data) createOrUpdatePriceChart(data.historical_data);
            if (data.daily_returns_histogram) createOrUpdateReturnHistogram(data.daily_returns_histogram); // Call histogram function

        } catch (error) {
            console.error('Full analysis fetch error:', error);
            alert(`Error fetching analysis: ${error.message}`);
            // Clear charts on error
            destroyAllCharts(); // Use the function to clear both charts
            // Optionally clear other UI fields here if needed
            // e.g., updateStockInfo(null), updateStatistics(null) etc. with appropriate handling in ui.js
        } finally {
            hideLoader();
        }
    }

    // --- WebSocket Connection Function ---
    function connectWebSocket(symbol) {
        // 1. Close any existing connection
        if (intradaySocket && intradaySocket.readyState !== WebSocket.CLOSED) {
            console.log("Closing previous WebSocket connection.");
            intradaySocket.onclose = null; // Prevent close handler from firing during manual close
            intradaySocket.close();
        }

        // Clear charts immediately when switching stocks
        // Note: fetchFullAnalysis also clears, but doing it here might feel slightly faster UI-wise
        // destroyAllCharts(); // Re-enable if needed, but might cause flicker

        // 2. Create a new connection
        const wsUrl = `${WS_BASE_URL}/intraday?symbol=${encodeURIComponent(symbol)}`;
        console.log("Connecting to WebSocket:", wsUrl);
        intradaySocket = new WebSocket(wsUrl);

        // 3. Set up listeners
        intradaySocket.onopen = (event) => {
            console.log("WebSocket connection opened for:", symbol);
            // Example: Send symbol after connection (if backend expects it)
            // intradaySocket.send(JSON.stringify({ "action": "subscribe", "symbol": symbol }));
        };

        intradaySocket.onmessage = (event) => {
             try {
                const message = JSON.parse(event.data);
                if (message.type === 'intraday_update' && message.data) {
                    updateIntradayWidget(message.data); // Update only the relevant widget
                } else {
                     console.warn("Received unexpected WebSocket message format:", message);
                }
             } catch (e) {
                  console.error("Error parsing WebSocket message:", e, event.data);
             }
        };

        intradaySocket.onclose = (event) => {
            // Check if closure was expected or an error
            if (event.wasClean) {
                 console.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
            } else {
                 console.warn('WebSocket connection died unexpectedly.');
                 // Optionally attempt to reconnect here after a delay
            }
            intradaySocket = null; // Clear reference
        };

        intradaySocket.onerror = (error) => {
            console.error("WebSocket error:", error);
            // The onclose event will usually fire after an error.
            intradaySocket = null; // Clear reference
        };
    }

    // --- Initial setup ---
     // You could fetch data for a default stock on page load if desired
     // fetchFullAnalysis('RELIANCE.NS');
     // connectWebSocket('RELIANCE.NS');
});