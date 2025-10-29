// finstock-ai/frontend/js/ui.js

// --- Loader ---
const loader = document.getElementById('loader-overlay');
const showLoader = () => loader.classList.remove('hidden');
const hideLoader = () => loader.classList.add('hidden');

// --- Tabbing ---
function setupTabs(widgetId) {
    const widget = document.getElementById(widgetId);
    if (!widget) return;
    const tabButtons = widget.querySelectorAll('.tab-btn');
    const tabContents = widget.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            button.classList.add('active');
            const targetContent = document.getElementById(button.dataset.tab);
            if (targetContent) targetContent.classList.add('active');
        });
    });
}

// --- Text/Value Helpers ---
function updateText(elementId, text, defaultValue = '-') {
    const el = document.getElementById(elementId);
    if (el) {
        if (text === null || typeof text === 'undefined' || (typeof text === 'number' && !isFinite(text))) {
            el.textContent = defaultValue;
        } else if (typeof text === 'number') {
             if (elementId.includes('price') || elementId.includes('value') || elementId.includes('mean') || elementId.includes('median')) {
                 el.textContent = `₹${text.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; // Use Indian locale for currency
             } else if (elementId.includes('percent') || elementId.includes('probability') || elementId.includes('prob_') || elementId.includes('return') || elementId.includes('streak')) {
                 el.textContent = `${text.toFixed(2)}%`;
             } else {
                 el.textContent = text.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }); // More precision for general stats
             }
        }
         else {
            el.textContent = text;
        }
    } else {
        console.warn(`UI Element not found: ${elementId}`);
    }
}

function updateSentiment(elementId, sentiment) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const effectiveSentiment = sentiment ?? 'Neutral';

    el.textContent = effectiveSentiment;
    el.classList.remove('text-green', 'text-red', 'text-neutral');

    if (effectiveSentiment === 'Positive') el.classList.add('text-green');
    else if (effectiveSentiment === 'Negative') el.classList.add('text-red');
    else el.classList.add('text-neutral');
}

// --- Main Data Population Functions ---

function updateStockInfo(stockInfo) {
    updateText('stock-name-header', stockInfo.longName || stockInfo.shortName, 'N/A');
    updateText('stock-symbol-header', stockInfo.symbol);
    updateText('stock-price-header', stockInfo.currentPrice);
    updateText('stock-sector-industry', `${stockInfo.sector || 'N/A'} | ${stockInfo.industry || 'N/A'}`);

    const changeEl = document.getElementById('stock-change-header');
    if (changeEl && stockInfo.currentPrice && stockInfo.previousClose) {
        const change = stockInfo.currentPrice - stockInfo.previousClose;
        const changePercent = (change / stockInfo.previousClose) * 100;
        changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)} (${change > 0 ? '+' : ''}${changePercent.toFixed(2)}%)`; // Add +/- sign
        changeEl.classList.remove('text-green', 'text-red', 'text-neutral');
        if (change > 0) changeEl.classList.add('text-green');
        else if (change < 0) changeEl.classList.add('text-red');
        else changeEl.classList.add('text-neutral');
    } else if (changeEl) {
        changeEl.textContent = '';
    }
}

function updateStatistics(statistics) {
    // Existing fields
    updateText('stat-start-date', statistics.start_date);
    updateText('stat-end-date', statistics.end_date);
    updateText('stat-mean', statistics.mean);
    updateText('stat-median', statistics.median);
    updateText('stat-std_deviation', statistics.std_deviation);
    updateText('stat-variance', statistics.variance);
    updateText('stat-skewness', statistics.skewness);
    updateText('stat-kurtosis', statistics.kurtosis);
    updateText('stat-probability_next_day_up', statistics.probability_next_day_up);

    // --- ADD LINES FOR NEW FIELDS ---
    updateText('stat-probability_next_day_down', statistics.probability_next_day_down);
    updateText('stat-mean_daily_return_percent', statistics.mean_daily_return_percent);
    updateText('stat-std_dev_daily_return_percent', statistics.std_dev_daily_return_percent);
    updateText('stat-cond_prob_up_given_up', statistics.cond_prob_up_given_up);
    updateText('stat-cond_prob_down_given_down', statistics.cond_prob_down_given_down);
    updateText('stat-prob_2_days_up_streak', statistics.prob_2_days_up_streak);
    updateText('stat-prob_2_days_down_streak', statistics.prob_2_days_down_streak);
}

function updateAIPredictions(aiPredictions) {
    updateText('pred-short-term-value', aiPredictions.short_term.forecast_7d_percent);
    updateText('pred-short-term-rec', aiPredictions.short_term.recommendation);
    updateText('pred-long-term-value', aiPredictions.long_term.forecast_1y);
    updateText('pred-long-term-rec', aiPredictions.long_term.recommendation);
    updateIntradayWidget(aiPredictions.intraday); // Initial snapshot
}

function updateNews(newsSentiment) {
    // Stock News
    updateSentiment('news-stock-sentiment span', newsSentiment.stock_news.overall_sentiment);
    const stockImpactEl = document.getElementById('news-stock-impact');
    if (stockImpactEl) stockImpactEl.textContent = ''; // Clear impact

    const stockArticlesEl = document.getElementById('stock-articles');
    if (stockArticlesEl) {
        stockArticlesEl.innerHTML = '';
        if (newsSentiment.stock_news.articles && newsSentiment.stock_news.articles.length > 0) {
            newsSentiment.stock_news.articles.forEach(article => {
                let sentimentClass = 'text-neutral';
                if (article.sentiment_label === 'Positive') sentimentClass = 'text-green';
                else if (article.sentiment_label === 'Negative') sentimentClass = 'text-red';

                stockArticlesEl.innerHTML += `
                    <div class="article">
                        <h5><span>${article.source || 'Source'}</span> ${article.headline || 'No Headline'} <span class="${sentimentClass}">(${article.sentiment_label || 'Neutral'})</span></h5>
                    </div>`;
            });
        } else {
             stockArticlesEl.innerHTML = '<p class="text-secondary">No relevant stock news found.</p>';
        }
    }

    // Market News
    updateSentiment('news-market-sentiment span', newsSentiment.global_market.overall_market_sentiment);
    const marketImpactEl = document.getElementById('news-market-impact');
     if (marketImpactEl) marketImpactEl.textContent = ''; // Clear impact

    const marketHeadlinesEl = document.getElementById('market-headlines');
    if (marketHeadlinesEl) {
        marketHeadlinesEl.innerHTML = '';
        if (newsSentiment.global_market.key_headlines && newsSentiment.global_market.key_headlines.length > 0) {
            newsSentiment.global_market.key_headlines.forEach(headline => {
                marketHeadlinesEl.innerHTML += `<div class="article"><p>${headline}</p></div>`;
            });
        } else {
             marketHeadlinesEl.innerHTML = '<p class="text-secondary">No market headlines found.</p>';
        }
    }
}

// --- Separate function for WebSocket updates ---
function updateIntradayWidget(intradayData) {
    if (!intradayData) return;
    console.log("Updating intraday widget with new data:", intradayData);
    updateText('pred-intraday-match', `Matches: ${intradayData.similar_pattern_found || 'N/A'} (Prob: ${intradayData.probability?.toFixed(2) || 'N/A'})`);
    updateText('pred-intraday-pred', intradayData.prediction || 'No prediction');
}